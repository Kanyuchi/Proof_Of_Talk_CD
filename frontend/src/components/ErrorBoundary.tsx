import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}
interface State {
  hasError: boolean;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surface in console for debugging; no external logging wired here.
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center px-4 text-center">
          <div className="max-w-md">
            <h1 className="text-xl font-semibold text-white mb-2">
              Something went wrong loading this page
            </h1>
            <p className="text-sm text-white/60 mb-6">
              This is usually a temporary network or browser issue. Please refresh,
              or try opening the link again. If it keeps happening, contact the
              Proof of Talk team.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="rounded-xl px-4 py-2 font-semibold text-white"
              style={{ background: "#E76315" }}
            >
              Refresh
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
