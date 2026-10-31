import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./theme.css";
import App from "./App";
import MockApp from "./MockApp";

const mock = new URLSearchParams(location.search).has("mock");
createRoot(document.getElementById("root")!).render(<StrictMode>{mock ? <MockApp /> : <App />}</StrictMode>);
