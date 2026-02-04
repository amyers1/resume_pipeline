import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AppProvider } from "./contexts/AppContext";
import { UserProvider } from "./contexts/UserContext";
import Header from "./components/Header";
import Dashboard from "./pages/Dashboard";
import NewJobPage from "./pages/NewJobPage";
import JobDetailPage from "./pages/JobDetailPage";
import ProfilesList from "./components/ProfilesList";
import ProfileView from "./components/ProfileView";
import ProfileEditor from "./components/ProfileEditor";

function App() {
    return (
        <AppProvider>
            <UserProvider>
                <Router>
                    <div className="min-h-screen bg-slate-50 dark:bg-background transition-colors">
                        <Header />
                        <main>
                            <Routes>
                                <Route path="/" element={<Dashboard />} />
                                <Route
                                    path="/new-job"
                                    element={<NewJobPage />}
                                />
                                <Route
                                    path="/jobs/:jobId"
                                    element={<JobDetailPage />}
                                />

                                {/* Profile Routes */}
                                <Route
                                    path="/profiles"
                                    element={<ProfilesList />}
                                />
                                <Route
                                    path="/profiles/new"
                                    element={<ProfileEditor />}
                                />
                                <Route
                                    path="/profiles/:profileId"
                                    element={<ProfileView />}
                                />
                                <Route
                                    path="/profiles/:profileId/edit"
                                    element={<ProfileEditor />}
                                />
                            </Routes>
                        </main>

                        {/* Toast Notifications */}
                        <Toaster
                            position="top-right"
                            reverseOrder={false}
                            gutter={8}
                            toastOptions={{
                                // Default options
                                duration: 3000,
                                style: {
                                    background: "var(--toast-bg, #363636)",
                                    color: "var(--toast-color, #fff)",
                                },
                                // Success
                                success: {
                                    duration: 3000,
                                    iconTheme: {
                                        primary: "#10b981",
                                        secondary: "#fff",
                                    },
                                },
                                // Error
                                error: {
                                    duration: 4000,
                                    iconTheme: {
                                        primary: "#ef4444",
                                        secondary: "#fff",
                                    },
                                },
                                // Loading
                                loading: {
                                    duration: Infinity,
                                },
                            }}
                        />
                    </div>
                </Router>
            </UserProvider>
        </AppProvider>
    );
}

export default App;
