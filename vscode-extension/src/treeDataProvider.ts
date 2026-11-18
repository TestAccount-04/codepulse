import * as vscode from 'vscode';
import { CodePulseClient } from './codepulseClient';
import { CodePulseSymbol, ReviewItem, ReviewStatus } from './types';

export class CodePulseTreeItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState,
    public readonly symbolData?: CodePulseSymbol,
    public readonly reviewData?: ReviewItem,
    public readonly filePath?: string
  ) {
    super(label, collapsibleState);

    if (symbolData) {
      this.contextValue = 'symbolItem';
      const status = reviewData?.status || 'pending';
      this.description = `[${symbolData.change_status}] • ${status.toUpperCase()}`;
      this.tooltip = new vscode.MarkdownString(
        `**${symbolData.name}** (${symbolData.symbol_type})\n\n` +
          `* File: \`${symbolData.file_path}\`\n` +
          `* Lines: ${symbolData.start_line} - ${symbolData.end_line}\n` +
          `* Change: \`${symbolData.change_status}\`\n` +
          `* Review: **${status.toUpperCase()}**\n` +
          (reviewData?.decision_reason ? `* Reason: *${reviewData.decision_reason}*\n` : '') +
          `* Annotations: ${reviewData?.annotations?.length || 0}`
      );

      // Icon based on review status
      if (status === 'accepted') {
        this.iconPath = new vscode.ThemeIcon('check', new vscode.ThemeColor('charts.green'));
      } else if (status === 'rejected') {
        this.iconPath = new vscode.ThemeIcon('discard', new vscode.ThemeColor('charts.red'));
      } else if (status === 'reviewed') {
        this.iconPath = new vscode.ThemeIcon('eye', new vscode.ThemeColor('charts.blue'));
      } else {
        this.iconPath = new vscode.ThemeIcon('circle-outline', new vscode.ThemeColor('charts.yellow'));
      }

      this.command = {
        command: 'codepulse.openSymbol',
        title: 'Open Symbol',
        arguments: [symbolData.file_path, symbolData.start_line],
      };
    } else if (filePath) {
      this.contextValue = 'fileItem';
      this.iconPath = vscode.ThemeIcon.File;
      this.resourceUri = vscode.Uri.file(filePath);
    }
  }
}

export class CodePulseTreeDataProvider implements vscode.TreeDataProvider<CodePulseTreeItem> {
  private _onDidChangeTreeData: vscode.EventEmitter<CodePulseTreeItem | undefined | null | void> =
    new vscode.EventEmitter<CodePulseTreeItem | undefined | null | void>();
  readonly onDidChangeTreeData: vscode.Event<CodePulseTreeItem | undefined | null | void> =
    this._onDidChangeTreeData.event;

  private symbols: CodePulseSymbol[] = [];
  private reviews: Map<string, ReviewItem> = new Map();
  private fileGroups: Map<string, CodePulseSymbol[]> = new Map();

  constructor(private client: CodePulseClient) {}

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: CodePulseTreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(element?: CodePulseTreeItem): Promise<CodePulseTreeItem[]> {
    if (!element) {
      // Root: fetch symbols and reviews from CodePulse API
      try {
        const [symbols, reviews] = await Promise.all([
          this.client.getChangedSymbols(),
          this.client.getReviews(),
        ]);
        this.symbols = symbols;
        this.reviews.clear();
        for (const r of reviews) {
          this.reviews.set(r.symbol_id, r);
        }

        if (this.symbols.length === 0) {
          const emptyItem = new CodePulseTreeItem(
            'No changed symbols detected',
            vscode.TreeItemCollapsibleState.None
          );
          emptyItem.description = 'Codebase clean';
          emptyItem.iconPath = new vscode.ThemeIcon('pass', new vscode.ThemeColor('charts.green'));
          return [emptyItem];
        }

        // Group symbols by file_path
        this.fileGroups.clear();
        for (const s of this.symbols) {
          const list = this.fileGroups.get(s.file_path) || [];
          list.push(s);
          this.fileGroups.set(s.file_path, list);
        }

        const items: CodePulseTreeItem[] = [];
        for (const [filePath, fileSymbols] of this.fileGroups.entries()) {
          const fileItem = new CodePulseTreeItem(
            filePath,
            vscode.TreeItemCollapsibleState.Expanded,
            undefined,
            undefined,
            filePath
          );
          fileItem.description = `${fileSymbols.length} changed`;
          items.push(fileItem);
        }
        return items;
      } catch (err: any) {
        const errorItem = new CodePulseTreeItem(
          'CodePulse server unavailable',
          vscode.TreeItemCollapsibleState.None
        );
        errorItem.description = 'Check codepulse start';
        errorItem.iconPath = new vscode.ThemeIcon('warning', new vscode.ThemeColor('charts.red'));
        errorItem.tooltip = err?.message || 'Cannot reach CodePulse backend';
        return [errorItem];
      }
    } else if (element.filePath) {
      // Child elements: symbols for this file
      const fileSymbols = this.fileGroups.get(element.filePath) || [];
      return fileSymbols.map((s) => {
        const review = this.reviews.get(s.id);
        return new CodePulseTreeItem(
          s.name,
          vscode.TreeItemCollapsibleState.None,
          s,
          review
        );
      });
    }

    return [];
  }
}
