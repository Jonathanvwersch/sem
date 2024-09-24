import * as vscode from "vscode";
import * as path from "path";
import { spawn } from "child_process";
import { SearchResultsProvider } from "./search-results";
import { MatchedFile } from "./types";

export class Commands {
  private pythonCommand: string;
  private searchResultsProvider: SearchResultsProvider;

  constructor(searchResultsProvider: SearchResultsProvider) {
    this.pythonCommand = path.join(
      __dirname,
      "..",
      "..",
      "semvec",
      ".venv",
      "bin",
      "python"
    );
    this.searchResultsProvider = searchResultsProvider;
  }

  async indexRepository() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
      vscode.window.showErrorMessage("No workspace folder open");
      return;
    }
    const repoPath = workspaceFolders[0].uri.fsPath;

    try {
      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Indexing repository. This can take up to a minute.",
          cancellable: false,
        },
        async () => {
          console.log("Starting indexing process");
          return new Promise<void>((resolve, reject) => {
            const pythonProcess = spawn(this.pythonCommand, [
              path.join(__dirname, "..", "..", "semvec", "core", "main.py"),
              "index",
              "--path",
              repoPath,
            ]);

            pythonProcess.stderr.on("data", (data) => {
              console.error(`stderr: ${data}`);
            });

            pythonProcess.on("close", (code) => {
              if (code === 0) {
                resolve();
              } else {
                reject(new Error(`Process exited with code ${code}`));
              }
            });
          });
        }
      );
      vscode.window.showInformationMessage("Repository indexed successfully");
    } catch (error) {
      console.error("Indexing error:", error);
      vscode.window.showErrorMessage(
        `Failed to index repository: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    }
  }

  async searchCode() {
    const query = await vscode.window.showInputBox({
      prompt: "Enter your semantic search query",
      placeHolder: "Search for code semantically...",
    });

    if (!query) {
      return;
    }

    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
      vscode.window.showErrorMessage("No workspace folder open");
      return;
    }
    const repoPath = workspaceFolders[0].uri.fsPath;

    try {
      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Searching Code",
          cancellable: false,
        },
        async () => {
          return new Promise<void>((resolve, reject) => {
            let jsonOutput = "";
            let isCapturingJson = false;
            let errorLogs = "";

            const pythonProcess = spawn(
              this.pythonCommand,
              [
                path.join(__dirname, "..", "..", "semvec", "core", "main.py"),
                "query",
                "--query",
                query,
                "--path",
                repoPath,
              ],
              { cwd: path.join(__dirname, "..", "..", "semvec", "core") }
            );

            pythonProcess.stdout.on("data", (data) => {
              const lines = data.toString().split("\n");

              for (const line of lines) {
                if (line.trim() === "START_JSON_OUTPUT") {
                  isCapturingJson = true;
                  jsonOutput = "";
                } else if (line.trim() === "END_JSON_OUTPUT") {
                  isCapturingJson = false;
                  try {
                    const result = JSON.parse(jsonOutput);
                    if (result.status === "error") {
                      reject(new Error(result.message));
                    } else {
                      resolve(result);
                    }
                  } catch (error) {
                    reject(new Error("Failed to parse JSON output"));
                  }
                } else if (isCapturingJson) {
                  jsonOutput += line;
                }
              }
            });

            pythonProcess.stderr.on("data", (data) => {
              errorLogs += data.toString();
              console.error(`Python stderr: ${data}`);
            });

            pythonProcess.on("close", (code) => {
              if (code === 0) {
                try {
                  if (jsonOutput) {
                    const parsedResults = JSON.parse(jsonOutput);
                    const updatedResults = parsedResults.map(
                      (result: MatchedFile) => ({
                        ...result,
                        file_path: path.join(repoPath, result.file_path),
                      })
                    );
                    this.searchResultsProvider.updateResults(updatedResults);
                    resolve();
                  } else {
                    throw new Error(
                      `Could not find JSON data in output ${jsonOutput}`
                    );
                  }
                } catch (error) {
                  console.error("JSON parsing error:", error);
                  console.log("Failed to parse JSON:", jsonOutput);
                  reject(
                    new Error(
                      `Failed to parse search results. JSON Output: ${jsonOutput}. Log Output: ${errorLogs}`
                    )
                  );
                }
              } else {
                reject(
                  new Error(
                    `Process exited with code ${code}. Error: ${errorLogs}`
                  )
                );
              }
            });
          });
        }
      );

      // Show the search results view
      await vscode.commands.executeCommand(
        "workbench.view.extension.semantic-search"
      );

      // Refresh the tree view
      this.searchResultsProvider.refresh();

      // Focus on the search results tree view
      await vscode.commands.executeCommand("semanticSearchResults.focus");
    } catch (error) {
      if (process.env.NODE_ENV === "development") {
        vscode.window
          .showErrorMessage(
            `Search failed: ${
              error instanceof Error ? error.message : "Unknown error"
            }`,
            "View Full Log"
          )
          .then((selection) => {
            if (selection === "View Full Log") {
              vscode.workspace
                .openTextDocument({
                  content: `Query: ${query}\n\nError: ${
                    error instanceof Error ? error.message : "Unknown error"
                  }\n\nFull log:\n${
                    error instanceof Error ? error.stack : "Unknown error"
                  }`,
                })
                .then((doc) => {
                  vscode.window.showTextDocument(doc);
                });
            }
          });
      } else {
        vscode.window.showErrorMessage(
          `Search failed: ${
            error instanceof Error ? error.message : "Unknown error"
          }`
        );
      }
    }
  }
}
