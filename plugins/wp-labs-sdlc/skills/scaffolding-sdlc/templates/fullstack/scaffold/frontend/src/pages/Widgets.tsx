import { useEffect, useState } from "react";
import { api } from "../lib/api";

interface Widget {
  id: number;
  name: string;
  created_at: string;
}

export function Widgets() {
  const [widgets, setWidgets] = useState<Widget[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Widget[]>("/widgets/")
      .then((res) => setWidgets(res.data))
      .catch(() => setError("Failed to load widgets"));
  }, []);

  return (
    <main>
      <h1>Widgets</h1>
      {error ? (
        <p role="alert">{error}</p>
      ) : (
        <ul>
          {widgets.map((w) => (
            <li key={w.id}>{w.name}</li>
          ))}
        </ul>
      )}
    </main>
  );
}
