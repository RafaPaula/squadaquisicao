import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import CategorizePage from "./pages/CategorizePage";
import ReviewPage from "./pages/ReviewPage";
import FunnelPage from "./pages/FunnelPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/categorizar" replace />} />
        <Route path="/categorizar" element={<CategorizePage />} />
        <Route path="/revisar" element={<ReviewPage />} />
        <Route path="/funil" element={<FunnelPage />} />
      </Route>
    </Routes>
  );
}
