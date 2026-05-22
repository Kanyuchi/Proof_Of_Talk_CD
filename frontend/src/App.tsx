import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./context/AuthContext";
import Layout from "./components/Layout";
import ErrorBoundary from "./components/ErrorBoundary";
import HomeLanding from "./pages/HomeLanding";
import Attendees from "./pages/Attendees";
import AttendeeMatches from "./pages/AttendeeMatches";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Profile from "./pages/Profile";
import MyMatches from "./pages/MyMatches";
import Messages from "./pages/Messages";
import NotFound from "./pages/NotFound";
import Onboarding from "./pages/Onboarding";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import MagicMatches from "./pages/MagicMatches";
import Briefing from "./pages/Briefing";
import Threads from "./pages/Threads";
import SponsorJoin from "./pages/SponsorJoin";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <ErrorBoundary>
          <Layout>
            <Routes>
              <Route path="/" element={<HomeLanding />} />
              <Route path="/attendees" element={<Attendees />} />
              <Route path="/attendees/:id" element={<AttendeeMatches />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/join/:code" element={<SponsorJoin />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/m/:token" element={<MagicMatches />} />
              <Route path="/m/:token/briefing" element={<Briefing />} />
              <Route path="/matches" element={<MyMatches />} />
              <Route path="/messages" element={<Messages />} />
              <Route path="/threads" element={<Threads />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/onboarding" element={<Onboarding />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Layout>
          </ErrorBoundary>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
