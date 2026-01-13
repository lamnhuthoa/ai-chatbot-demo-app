import ChatPage from "./components/ChatPage";
import "./App.css";
import {
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

const App = () => {
  return (
    <Routes>
      <Route path="/" element={<ChatPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;
