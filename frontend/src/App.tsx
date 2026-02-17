import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import Attendees from "./pages/Attendees";
import AttendeeMatches from "./pages/AttendeeMatches";
import Dashboard from "./pages/Dashboard";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/attendees" element={<Attendees />} />
            <Route path="/attendees/:id" element={<AttendeeMatches />} />
            <Route path="/dashboard" element={<Dashboard />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
