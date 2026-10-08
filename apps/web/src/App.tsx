import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { Layout } from "./components/Layout";
import { Architecture } from "./pages/Architecture";
import { Dashboard } from "./pages/Dashboard";
import { RequestDetails } from "./pages/RequestDetails";

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Dashboard /> },
      { path: "/requests/:id", element: <RequestDetails /> },
      { path: "/requests/:id/execution", element: <RequestDetails executionOpen /> },
      { path: "/architecture", element: <Architecture /> },
    ],
  },
]);

export function App() {
  return <RouterProvider router={router} />;
}
