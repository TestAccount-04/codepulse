import * as vscode from 'vscode';
import { CodePulseClient } from './codepulseClient';
import { AgentSessionSummary } from './types';

export class SessionTreeItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly description?: string,
    public readonly tooltipText?: string,
    public readonly icon?: vscode.ThemeIcon
  ) {
    super(label, vscode.TreeItemCollapsibleState.None);
    if (description) this.description = description;
    if (tooltipText) this.tooltip = tooltipText;
    if (icon) this.iconPath = icon;
  }
}

export class SessionDataProvider implements vscode.TreeDataProvider<SessionTreeItem> {
  private _onDidChangeTreeData: vscode.EventEmitter<SessionTreeItem | undefined | null | void> =
    new vscode.EventEmitter<SessionTreeItem | undefined | null | void>();
  readonly onDidChangeTreeData: vscode.Event<SessionTreeItem | undefined | null | void> =
    this._onDidChangeTreeData.event;

  constructor(private client: CodePulseClient) {}

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: SessionTreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(): Promise<SessionTreeItem[]> {
    try {
      const sessions = await this.client.getActiveSessions();
      if (!sessions || sessions.length === 0) {
        return [
          new SessionTreeItem(
            'No Active Agent Session',
            'Idle',
            'No coding agent session recorded',
            new vscode.ThemeIcon('circle-slash')
          ),
        ];
      }

      const active = sessions[0];
      const items: SessionTreeItem[] = [
        new SessionTreeItem(
          `Agent: ${active.agent_name}`,
          active.status.toUpperCase(),
          `Session ID: ${active.id}`,
          new vscode.ThemeIcon('robot')
        ),
      ];

      if (active.task_description) {
        items.push(
          new SessionTreeItem(
            'Task Goal',
            active.task_description.slice(0, 40) + '...',
            active.task_description,
            new vscode.ThemeIcon('note')
          )
        );
      }

      items.push(
        new SessionTreeItem(
          'Started At',
          active.started_at.slice(11, 19),
          active.started_at,
          new vscode.ThemeIcon('clock')
        )
      );

      return items;
    } catch {
      return [
        new SessionTreeItem(
          'CodePulse Server Offline',
          undefined,
          'Start backend using codepulse start',
          new vscode.ThemeIcon('warning')
        ),
      ];
    }
  }
}
