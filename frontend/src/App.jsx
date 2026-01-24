import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
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
                    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
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
                    </div>
                </Router>
            </UserProvider>
        </AppProvider>
    );
}

export default App;
