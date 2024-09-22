import * as vscode from "vscode";
import { Commands } from "./commands";
import { SearchResultsProvider } from "./search-results";

export function activate(context: vscode.ExtensionContext) {
  console.log("Semantic Search extension is now active");
  const searchResultsProvider = new SearchResultsProvider();
  const commands = new Commands(searchResultsProvider);

  vscode.window.registerTreeDataProvider(
    "semanticSearchResults",
    searchResultsProvider
  );

  const allCommands = {
    index: vscode.commands.registerCommand("semsearch.indexRepository", () =>
      commands.indexRepository()
    ),
    search: vscode.commands.registerCommand("semsearch.searchCode", () =>
      commands.searchCode()
    ),
  };

  context.subscriptions.push(allCommands.index, allCommands.search);
}

export function deactivate() {}
