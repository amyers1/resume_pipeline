import { createContext, useContext, useState, useEffect } from "react";
import { apiService } from "../services/api";

const UserContext = createContext(null);

export function UserProvider({ children }) {
    const [currentUser, setCurrentUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadUser();
    }, []);

    const loadUser = async () => {
        try {
            setLoading(true);
            // Get the first user (or implement proper auth)
            const response = await apiService.listUsers();
            if (response.data && response.data.length > 0) {
                setCurrentUser(response.data[0]);
            }
        } catch (error) {
            console.error("Failed to load user:", error);
        } finally {
            setLoading(false);
        }
    };

    const value = {
        currentUser,
        loading,
        refreshUser: loadUser,
    };

    return (
        <UserContext.Provider value={value}>{children}</UserContext.Provider>
    );
}

export function useUser() {
    const context = useContext(UserContext);
    if (!context) {
        throw new Error("useUser must be used within a UserProvider");
    }
    return context;
}
