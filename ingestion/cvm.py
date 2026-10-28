"""Immutable content-addressed files and bounded CVM CSV envelopes.

No inferred business calendar, automatic correction, or arbitrary schema coercion.
"""
import csv,hashlib,io,json,os,pathlib,re,tempfile,zipfile
REQUIRED={'TP_FUNDO_CLASSE','CNPJ_FUNDO_CLASSE','ID_SUBCLASSE','DT_COMPTC','VL_TOTAL','VL_QUOTA','VL_PATRIM_LIQ','CAPTC_DIA','RESG_DIA','NR_COTST'}

def land(data, root):
    root=pathlib.Path(root);root.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(data).hexdigest();path=root/digest
    if path.exists():
        if path.read_bytes()!=data:raise ValueError('Immutable object corrupted')
        return path
    fd,temp=tempfile.mkstemp(dir=root)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.chmod(temp,0o444)
        try:os.link(temp,path)
        except FileExistsError:
            if path.read_bytes()!=data:raise ValueError('Immutable object collision/corruption')
    finally:os.unlink(temp)
    return path

def envelopes(data, members):
    result=[];excluded=0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            infos=z.infolist()
            if len(infos)!=1 or pathlib.PurePosixPath(infos[0].filename).name!=infos[0].filename or not re.fullmatch(r'inf_diario_fi_[0-9]{6}\.csv',infos[0].filename):
                raise ValueError('Unexpected archive member')
            if infos[0].file_size>1_000_000_000:raise ValueError('Uncompressed limit exceeded')
            member=infos[0].filename;period=member[-10:-4]
            with z.open(member) as binary:
                reader=csv.reader(io.TextIOWrapper(binary,encoding='latin1',newline=''),delimiter=';',strict=True)
                header=next(reader)
                if len(set(header))!=len(header) or not REQUIRED.issubset(header):raise ValueError('Required CSV schema missing or duplicate header')
                previous_line=reader.line_num
                for number,values in enumerate(reader,1):
                    line_start=previous_line+1;line_end=reader.line_num;previous_line=line_end
                    row=dict(zip(header,values));identifier=row.get('CNPJ_FUNDO_CLASSE','')
                    valid=re.fullmatch(r'[0-9]{14}|[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}',identifier)
                    error='csv_width' if len(values)!=len(header) else ('invalid_cnpj' if not valid else None)
                    cnpj=re.sub(r'[^0-9]','',identifier)
                    # Unclassifiable records fail closed; they cannot silently disappear outside the cohort.
                    if error is None and cnpj not in members:excluded+=1;continue
                    if error is None and set(header)!=REQUIRED:error='unknown_columns'
                    payload={'schema_version':1,'data':{k:(v if v!='' else None) for k,v in row.items()},'error':error}
                    if error:payload['raw_fields']=values
                    result.append({'member':member,'record_number':number,'line_start':line_start,'line_end':line_end,'period':period,'payload':json.dumps(payload,ensure_ascii=False,separators=(',',':'))})
    except (zipfile.BadZipFile,csv.Error,StopIteration,UnicodeError) as exc:
        raise ValueError('Unreadable or structurally invalid CSV/ZIP') from exc
    return result,excluded
