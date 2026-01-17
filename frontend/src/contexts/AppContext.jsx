import { createContext, useContext, useReducer, useEffect } from 'react';
import { apiService } from '../services/api';

const AppContext = createContext();

// Initial state
const initialState = {
  health: {
    status: 'unknown',
    checks: {},
    lastChecked: null,
  },
  jobs: {
    list: [],
    current: null,
    isLoading: false,
    error: null,
    pagination: {
      page: 1,
      pageSize: 20,
      totalCount: 0,
      totalPages: 0,
    },
  },
  profiles: {
    available: [],
    selected: null,
  },
  ui: {
    theme: localStorage.getItem('theme') || 'light',
    sidebarOpen: true,
  },
};

// Action types
const actionTypes = {
  SET_HEALTH: 'SET_HEALTH',
  SET_JOBS: 'SET_JOBS',
  SET_CURRENT_JOB: 'SET_CURRENT_JOB',
  SET_JOBS_LOADING: 'SET_JOBS_LOADING',
  SET_JOBS_ERROR: 'SET_JOBS_ERROR',
  UPDATE_JOB_STATUS: 'UPDATE_JOB_STATUS',
  ADD_JOB: 'ADD_JOB',
  REMOVE_JOB: 'REMOVE_JOB',
  SET_PROFILES: 'SET_PROFILES',
  SET_SELECTED_PROFILE: 'SET_SELECTED_PROFILE',
  TOGGLE_THEME: 'TOGGLE_THEME',
  TOGGLE_SIDEBAR: 'TOGGLE_SIDEBAR',
};

// Reducer
const appReducer = (state, action) => {
  switch (action.type) {
    case actionTypes.SET_HEALTH:
      return {
        ...state,
        health: {
          ...action.payload,
          lastChecked: new Date(),
        },
      };

    case actionTypes.SET_JOBS:
      return {
        ...state,
        jobs: {
          ...state.jobs,
          list: action.payload.jobs,
          pagination: {
            page: action.payload.page,
            pageSize: action.payload.page_size,
            totalCount: action.payload.total_count,
            totalPages: action.payload.total_pages,
          },
          isLoading: false,
        },
      };

    case actionTypes.SET_CURRENT_JOB:
      return {
        ...state,
        jobs: {
          ...state.jobs,
          current: action.payload,
        },
      };

    case actionTypes.SET_JOBS_LOADING:
      return {
        ...state,
        jobs: {
          ...state.jobs,
          isLoading: action.payload,
        },
      };

    case actionTypes.SET_JOBS_ERROR:
      return {
        ...state,
        jobs: {
          ...state.jobs,
          error: action.payload,
          isLoading: false,
        },
      };

    case actionTypes.UPDATE_JOB_STATUS:
      return {
        ...state,
        jobs: {
          ...state.jobs,
          list: state.jobs.list.map((job) =>
            job.job_id === action.payload.job_id
              ? { ...job, ...action.payload }
              : job
          ),
          current:
            state.jobs.current?.job_id === action.payload.job_id
              ? { ...state.jobs.current, ...action.payload }
              : state.jobs.current,
        },
      };

    case actionTypes.ADD_JOB:
      return {
        ...state,
        jobs: {
          ...state.jobs,
          list: [action.payload, ...state.jobs.list],
        },
      };

    case actionTypes.REMOVE_JOB:
      return {
        ...state,
        jobs: {
          ...state.jobs,
          list: state.jobs.list.filter((job) => job.job_id !== action.payload),
          current:
            state.jobs.current?.job_id === action.payload
              ? null
              : state.jobs.current,
        },
      };

    case actionTypes.SET_PROFILES:
      return {
        ...state,
        profiles: {
          ...state.profiles,
          available: action.payload,
        },
      };

    case actionTypes.SET_SELECTED_PROFILE:
      return {
        ...state,
        profiles: {
          ...state.profiles,
          selected: action.payload,
        },
      };

    case actionTypes.TOGGLE_THEME:
      const newTheme = state.ui.theme === 'light' ? 'dark' : 'light';
      localStorage.setItem('theme', newTheme);
      return {
        ...state,
        ui: {
          ...state.ui,
          theme: newTheme,
        },
      };

    case actionTypes.TOGGLE_SIDEBAR:
      return {
        ...state,
        ui: {
          ...state.ui,
          sidebarOpen: !state.ui.sidebarOpen,
        },
      };

    default:
      return state;
  }
};

// Provider component
export const AppProvider = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // Apply theme to document
  useEffect(() => {
    if (state.ui.theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [state.ui.theme]);

  // Health check on mount and periodically
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await apiService.checkHealth();
        dispatch({ type: actionTypes.SET_HEALTH, payload: response.data });
      } catch (error) {
        console.error('Health check failed:', error);
        dispatch({
          type: actionTypes.SET_HEALTH,
          payload: { status: 'unhealthy', checks: {} },
        });
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const value = {
    state,
    dispatch,
    actionTypes,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

// Custom hook to use the context
export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
