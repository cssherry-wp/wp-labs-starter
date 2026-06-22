/** Build a greeting for the given name. */
export function greet(name: string): string {
  const trimmed = name.trim();
  if (trimmed === "") {
    throw new Error("name must not be empty");
  }
  return `Hello, ${trimmed}!`;
}
