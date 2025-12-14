/**
 * Agent SDK TypeScript Example
 *
 * This script demonstrates that the Claude Agent SDK works without a separate
 * API key - it uses your existing Claude Code login (Max/Team/Enterprise).
 *
 * Key insight: The Agent SDK is "headless Claude Code" - it reuses your
 * subscription, not a separate API billing account.
 */

import Anthropic from "@anthropic-ai/claude-code";

async function main(): Promise<void> {
  console.log("=".repeat(60));
  console.log("Claude Agent SDK Demo");
  console.log("=".repeat(60));
  console.log();
  console.log("This example proves: If Claude Code works, Agent SDK works.");
  console.log("No separate API key needed - uses your Claude Code login.");
  console.log();

  // Create the client - no API key configuration needed!
  // The SDK automatically uses your Claude Code authentication.
  const client = new Anthropic();

  console.log("Querying Claude to list flows in this repository...");
  console.log("-".repeat(60));
  console.log();

  try {
    // Simple query: ask Claude to list the flows defined in this repo
    const response = await client.messages.create({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1024,
      messages: [
        {
          role: "user",
          content:
            "List the 6 SDLC flows defined in this Flow Studio repository. " +
            "Just give me a brief one-line description of each flow (1-6). " +
            "Look at swarm/flows/ or CLAUDE.md for this information.",
        },
      ],
    });

    // Extract and display the response
    const textContent = response.content.find((block) => block.type === "text");
    if (textContent && textContent.type === "text") {
      console.log("Response from Claude:");
      console.log();
      console.log(textContent.text);
    }

    console.log();
    console.log("-".repeat(60));
    console.log("Success! The Agent SDK connected without an API key.");
    console.log();
    console.log("What this proves:");
    console.log("  1. Agent SDK reuses your Claude Code subscription");
    console.log("  2. No separate API billing account needed");
    console.log("  3. Works if you're logged into Claude Code");
    console.log();
  } catch (error) {
    console.error();
    console.error("Error occurred:");
    console.error();

    if (error instanceof Error) {
      if (error.message.includes("authentication") || error.message.includes("401")) {
        console.error("Authentication failed. Make sure you are:");
        console.error("  1. Logged into Claude Code (run 'claude' in terminal)");
        console.error("  2. Have an active Claude subscription (Max/Team/Enterprise)");
        console.error();
        console.error("The Agent SDK uses your Claude Code login, not a separate API key.");
      } else {
        console.error(error.message);
      }
    } else {
      console.error(String(error));
    }

    process.exit(1);
  }
}

// Run the demo
main().catch((error) => {
  console.error("Unexpected error:", error);
  process.exit(1);
});
