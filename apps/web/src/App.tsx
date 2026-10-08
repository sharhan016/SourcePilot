import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { Layout } from "./components/Layout";
import { Architecture } from "./pages/Architecture";
import { Dashboard } from "./pages/Dashboard";
import { Execution } from "./pages/Execution";
import { RequestDetails } from "./pages/RequestDetails";

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Dashboard /> },
      { path: "/requests/:id", element: <RequestDetails /> },
      { path: "/requests/:id/execution", element: <Execution /> },
      { path: "/architecture", element: <Architecture /> },
    ],
  },
]);

export function App() {
  return <RouterProvider router={router} />;
}

