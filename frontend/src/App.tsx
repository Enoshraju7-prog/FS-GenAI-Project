import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import ProtectedRoute from "@/components/ProtectedRoute"
import ChatLayout from "@/pages/ChatLayout"
import LoginPage from "@/pages/LoginPage"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/chats" element={<ChatLayout />} />
          <Route path="/chats/:threadId" element={<ChatLayout />} />
        </Route>
        <Route path="*" element={<Navigate to="/chats" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
