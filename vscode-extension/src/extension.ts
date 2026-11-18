import * as vscode from 'vscode';
import * as path from 'path';
import { CodePulseClient } from './codepulseClient';
import { CodePulseTreeDataProvider, CodePulseTreeItem } from './treeDataProvider';
import { SessionDataProvider } from './sessionDataProvider';

export function activate(context: vscode.ExtensionContext) {
  const config = vscode.workspace.getConfiguration('codepulse');
  const backendUrl = config.get<string>('backendUrl', 'http://127.0.0.1:8000');
  const client = new CodePulseClient(backendUrl);

  const changesProvider = new CodePulseTreeDataProvider(client);
  const sessionProvider = new SessionDataProvider(client);

  vscode.window.registerTreeDataProvider('codepulse.changesView', changesProvider);
  vscode.window.registerTreeDataProvider('codepulse.sessionView', sessionProvider);

  // Status Bar Item
  const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  statusBarItem.command = 'codepulse.refresh';
  statusBarItem.text = '$(pulse) CodePulse';
  statusBarItem.tooltip = 'Click to refresh CodePulse status';
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  const updateStatusBar = async () => {
    try {
      const healthy = await client.isHealthy();
      if (!healthy) {
        statusBarItem.text = '$(pulse) CodePulse (Offline)';
        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        return;
      }
      statusBarItem.backgroundColor = undefined;
      const symbols = await client.getChangedSymbols();
      const reviews = await client.getReviews();
      const pendingCount = symbols.filter((s) => {
        const rev = reviews.find((r) => r.symbol_id === s.id);
        return !rev || rev.status === 'pending';
      }).length;

      if (symbols.length === 0) {
        statusBarItem.text = '$(pulse) CodePulse: Clean';
      } else {
        statusBarItem.text = `$(pulse) CodePulse: ${symbols.length} Changed (${pendingCount} Pending)`;
      }
    } catch {
      statusBarItem.text = '$(pulse) CodePulse (Error)';
    }
  };

  // Commands
  const refreshCommand = vscode.commands.registerCommand('codepulse.refresh', async () => {
    changesProvider.refresh();
    sessionProvider.refresh();
    await updateStatusBar();
  });

  const openSymbolCommand = vscode.commands.registerCommand(
    'codepulse.openSymbol',
    async (filePath: string, line: number) => {
      const workspaceFolders = vscode.workspace.workspaceFolders;
      if (!workspaceFolders || workspaceFolders.length === 0) return;

      const rootPath = workspaceFolders[0].uri.fsPath;
      const fullPath = path.isAbsolute(filePath) ? filePath : path.join(rootPath, filePath);
      const uri = vscode.Uri.file(fullPath);

      try {
        const doc = await vscode.workspace.openTextDocument(uri);
        const editor = await vscode.window.showTextDocument(doc);
        const targetLine = Math.max(0, line - 1);
        const pos = new vscode.Position(targetLine, 0);
        editor.selection = new vscode.Selection(pos, pos);
        editor.revealRange(
          new vscode.Range(pos, pos),
          vscode.TextEditorRevealType.InCenter
        );
      } catch (err: any) {
        vscode.window.showErrorMessage(`Failed to open ${filePath}: ${err?.message}`);
      }
    }
  );

  const acceptChangeCommand = vscode.commands.registerCommand(
    'codepulse.acceptChange',
    async (item?: CodePulseTreeItem) => {
      if (!item?.symbolData) {
        vscode.window.showWarningMessage('Select a changed symbol to accept.');
        return;
      }
      try {
        await client.setReviewStatus(item.symbolData.id, 'accepted');
        vscode.window.showInformationMessage(
          `Accepted change for '${item.symbolData.name}'. (Repository files preserved)`
        );
        changesProvider.refresh();
        await updateStatusBar();
      } catch (err: any) {
        vscode.window.showErrorMessage(`Failed to accept change: ${err?.message}`);
      }
    }
  );

  const rejectChangeCommand = vscode.commands.registerCommand(
    'codepulse.rejectChange',
    async (item?: CodePulseTreeItem) => {
      if (!item?.symbolData) {
        vscode.window.showWarningMessage('Select a changed symbol to reject.');
        return;
      }
      const sym = item.symbolData;
      const confirm = await vscode.window.showWarningMessage(
        `Are you sure you want to reject and rollback '${sym.name}'? Unrelated user edits will be preserved.`,
        { modal: true },
        'Reject & Rollback'
      );
      if (confirm !== 'Reject & Rollback') return;

      try {
        const res = await client.rollbackSymbol(sym.id, 'Rejected by developer in VS Code');
        if (res.success) {
          vscode.window.showInformationMessage(
            `Change rejected: ${res.message || 'Safely rolled back.'}`
          );
        }
        changesProvider.refresh();
        await updateStatusBar();
      } catch (err: any) {
        vscode.window.showErrorMessage(`Rollback failed: ${err?.message}`);
      }
    }
  );

  const markReviewedCommand = vscode.commands.registerCommand(
    'codepulse.markReviewed',
    async (item?: CodePulseTreeItem) => {
      if (!item?.symbolData) return;
      try {
        await client.setReviewStatus(item.symbolData.id, 'reviewed');
        vscode.window.showInformationMessage(`Marked '${item.symbolData.name}' as reviewed.`);
        changesProvider.refresh();
        await updateStatusBar();
      } catch (err: any) {
        vscode.window.showErrorMessage(`Failed to mark reviewed: ${err?.message}`);
      }
    }
  );

  const addNoteCommand = vscode.commands.registerCommand(
    'codepulse.addNote',
    async (item?: CodePulseTreeItem) => {
      if (!item?.symbolData) return;
      const note = await vscode.window.showInputBox({
        prompt: `Add review note for '${item.symbolData.name}'`,
        placeHolder: 'e.g. Needs unit test coverage or null safety check',
      });
      if (!note || !note.trim()) return;

      try {
        await client.addReviewNote(item.symbolData.id, note.trim());
        vscode.window.showInformationMessage(`Note attached to '${item.symbolData.name}'.`);
        changesProvider.refresh();
      } catch (err: any) {
        vscode.window.showErrorMessage(`Failed to add note: ${err?.message}`);
      }
    }
  );

  const showImpactCommand = vscode.commands.registerCommand(
    'codepulse.showImpact',
    async (item?: CodePulseTreeItem) => {
      if (!item?.symbolData) return;
      try {
        const detail = await client.getReviewDetail(item.symbolData.id);
        const exp = detail.explanation;
        const callers = detail.impact_report?.direct_callers || [];

        const outputChannel = vscode.window.createOutputChannel('CodePulse Review');
        outputChannel.clear();
        outputChannel.appendLine(`=========================================`);
        outputChannel.appendLine(`CodePulse Review & Impact Analysis`);
        outputChannel.appendLine(`Symbol: ${detail.symbol_name} (${detail.file_path})`);
        outputChannel.appendLine(`Status: ${detail.status.toUpperCase()} | Risk: ${exp?.risk_level || 'LOW'}`);
        outputChannel.appendLine(`=========================================\n`);

        if (exp) {
          outputChannel.appendLine(`[WHAT CHANGED]`);
          outputChannel.appendLine(`${exp.what_changed}\n`);
          outputChannel.appendLine(`[WHY]`);
          outputChannel.appendLine(`${exp.why}\n`);
          outputChannel.appendLine(`[IMPACT]`);
          outputChannel.appendLine(`${exp.impact}\n`);
        }

        outputChannel.appendLine(`[DIRECT CALLERS (${callers.length})]`);
        for (const c of callers) {
          outputChannel.appendLine(`  - ${c.caller_name} at ${c.file_path}:${c.line}`);
        }
        if (callers.length === 0) {
          outputChannel.appendLine(`  (No direct callers detected)`);
        }

        outputChannel.appendLine(`\n[REVIEW ANNOTATIONS (${detail.annotations.length})]`);
        for (const a of detail.annotations) {
          outputChannel.appendLine(`  [${a.author}] ${a.note} (${a.created_at})`);
        }

        outputChannel.show();
      } catch (err: any) {
        vscode.window.showErrorMessage(`Failed to load impact detail: ${err?.message}`);
      }
    }
  );

  const openDashboardCommand = vscode.commands.registerCommand('codepulse.openDashboard', () => {
    const url = vscode.Uri.parse(client.getBaseUrl());
    vscode.env.openExternal(url);
  });

  context.subscriptions.push(
    refreshCommand,
    openSymbolCommand,
    acceptChangeCommand,
    rejectChangeCommand,
    markReviewedCommand,
    addNoteCommand,
    showImpactCommand,
    openDashboardCommand
  );

  // Auto-refresh timer
  const intervalSeconds = config.get<number>('autoRefreshInterval', 5);
  if (intervalSeconds > 0) {
    const timer = setInterval(() => {
      changesProvider.refresh();
      sessionProvider.refresh();
      updateStatusBar();
    }, intervalSeconds * 1000);
    context.subscriptions.push({ dispose: () => clearInterval(timer) });
  }

  // Initial update
  updateStatusBar();
}

export function deactivate() {}
