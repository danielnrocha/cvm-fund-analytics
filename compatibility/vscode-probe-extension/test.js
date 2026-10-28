const vscode=require('vscode');
const fs=require('fs');
const path=require('path');
exports.run=async()=>{
 const root=vscode.workspace.workspaceFolders[0].uri.fsPath;
 const output=path.join(root,'evidence/25-vscode.json');
 const result={vscode:vscode.version};
 const ext=vscode.extensions.getExtension('dbtLabsInc.dbt');
 await ext.activate();
 result.extension={version:ext.packageJSON.version,active:ext.isActive};
 const doc=await vscode.workspace.openTextDocument(path.join(root,'models/fct_shipments.sql'));
 await vscode.window.showTextDocument(doc);
 const start=Date.now();
 while(Date.now()-start<15000){
   const symbols=await vscode.commands.executeCommand('vscode.executeDocumentSymbolProvider',doc.uri);
   if(symbols&&symbols.length){result.symbols=symbols;break;}
   await new Promise(r=>setTimeout(r,1000));
 }
 result.sqlDiagnosticProbe = {};
 const probePath=path.join(root,'models/editor_diagnostic_probe.sql');
 try {
   fs.writeFileSync(probePath,"select definitely_missing_column from {{ ref('shipments') }}\n");
   const badDoc=await vscode.workspace.openTextDocument(probePath);
   await vscode.window.showTextDocument(badDoc);
   const until=Date.now()+12000;
   let diagnostics=[];
   while(Date.now()<until){
     diagnostics=vscode.languages.getDiagnostics(badDoc.uri);
     if(diagnostics.some(d=>d.severity===0)) break;
     await new Promise(r=>setTimeout(r,500));
   }
   result.sqlDiagnosticProbe.diagnostics=diagnostics.map(d=>({message:d.message,severity:d.severity}));
   result.sqlDiagnosticProbe.detected=diagnostics.some(d=>d.severity===0);
 } finally {fs.unlinkSync(probePath);}
 await vscode.window.showTextDocument(doc);
 result.language=doc.languageId;
 result.diagnostics=vscode.languages.getDiagnostics(doc.uri).map(d=>({message:d.message,severity:d.severity}));
 result.commands=(await vscode.commands.getCommands()).filter(c=>['dbt.showColumnLineage','dbt.compileFile','dbt.buildProject'].includes(c));
 const task=new vscode.Task({type:'shell'},vscode.TaskScope.Workspace,'compatibility-build','probe',new vscode.ProcessExecution(path.join(root,'.venv-dbt/bin/dbt'),['build','--profiles-dir',root],{cwd:root,env:{DBT_SEND_ANONYMOUS_USAGE_STATS:'false'}}));
 result.task=await new Promise(async(resolve,reject)=>{
   const timeout=setTimeout(()=>reject(new Error('task timed out')),60000);
   const sub=vscode.tasks.onDidEndTaskProcess(e=>{if(e.execution.task.name===task.name){clearTimeout(timeout);sub.dispose();resolve({exitCode:e.exitCode});}});
   await vscode.tasks.executeTask(task);
 });
 fs.writeFileSync(output,JSON.stringify(result,null,2));
 if(result.task.exitCode!==0) throw new Error('VS Code task build failed');
};
