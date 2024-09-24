import * as vscode from "vscode";
import * as path from "path";

export class SearchResultItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState,
    public readonly score: number,
    public readonly filePath: string,
    public readonly startLine: number,
    public readonly endLine: number
  ) {
    super(label, collapsibleState);
    this.tooltip = `File: ${filePath}\nLines: ${startLine}-${endLine}\nScore: ${score.toFixed(
      4
    )}`;
    this.description = `(Score: ${score.toFixed(4)})`;
    this.command = {
      command: "vscode.open",
      title: "Open File",
      arguments: [
        vscode.Uri.file(filePath),
        {
          selection: new vscode.Range(startLine - 1, 0, endLine - 1, 0),
        },
      ],
    };
    this.iconPath = new vscode.ThemeIcon(
      collapsibleState === vscode.TreeItemCollapsibleState.None
        ? "symbol-field"
        : "symbol-file"
    );
    this.contextValue =
      collapsibleState === vscode.TreeItemCollapsibleState.None
        ? "searchResult"
        : "fileResult";
  }
}

export class SearchResultsProvider
  implements vscode.TreeDataProvider<SearchResultItem>
{
  private _onDidChangeTreeData: vscode.EventEmitter<
    SearchResultItem | undefined | null | void
  > = new vscode.EventEmitter<SearchResultItem | undefined | null | void>();
  readonly onDidChangeTreeData: vscode.Event<
    SearchResultItem | undefined | null | void
  > = this._onDidChangeTreeData.event;

  private results: Map<string, SearchResultItem[]> = new Map();

  public refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  public updateResults(results: any[]): void {
    this.results.clear();
    results.forEach((result) => {
      if (!this.results.has(result.file_path)) {
        this.results.set(result.file_path, []);
      }
      this.results
        .get(result.file_path)!
        .push(
          new SearchResultItem(
            `Lines ${result.start_line}-${result.end_line}`,
            vscode.TreeItemCollapsibleState.None,
            result.score,
            result.file_path,
            result.start_line,
            result.end_line
          )
        );
    });
    this.refresh();
  }

  getTreeItem(element: SearchResultItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: SearchResultItem): Thenable<SearchResultItem[]> {
    if (!element) {
      const items = Array.from(this.results.entries()).map(
        ([filePath, items]) => {
          return new SearchResultItem(
            path.basename(filePath),
            vscode.TreeItemCollapsibleState.Expanded,
            Math.max(...items.map((item) => item.score)),
            filePath,
            items[0].startLine,
            items[items.length - 1].endLine
          );
        }
      );
      return Promise.resolve(items);
    } else if (
      element.collapsibleState === vscode.TreeItemCollapsibleState.Expanded
    ) {
      const children = this.results.get(element.filePath) || [];
      return Promise.resolve(children);
    }
    return Promise.resolve([]);
  }

  getParent(
    element: SearchResultItem
  ): vscode.ProviderResult<SearchResultItem> {
    if (element.collapsibleState === vscode.TreeItemCollapsibleState.None) {
      // This is a child item, so find its parent
      for (const [filePath, items] of this.results.entries()) {
        if (items.includes(element)) {
          return new SearchResultItem(
            path.basename(filePath),
            vscode.TreeItemCollapsibleState.Expanded,
            Math.max(...items.map((item) => item.score)),
            filePath,
            items[0].startLine,
            items[items.length - 1].endLine
          );
        }
      }
    }
    return null; // Root items have no parent
  }
}
