import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { Home } from "./pages/Home";
import { Widgets } from "./pages/Widgets";

/** Route table, exported separately so tests can mount it in a MemoryRouter. */
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/widgets" element={<Widgets />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <nav>
        <Link to="/">Home</Link> | <Link to="/widgets">Widgets</Link>
      </nav>
      <AppRoutes />
    </BrowserRouter>
  );
}
