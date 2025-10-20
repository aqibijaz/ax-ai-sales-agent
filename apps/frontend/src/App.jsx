import React from "react";
import Chatbot from "./components/Chatbot";

function App() {
  return (
    <div className="h-screen bg-gray-100">
      <h1 className="text-3xl font-bold text-center mt-10">Welcome to AccellionX</h1>
      {/* Add the floating chatbot */}
      <Chatbot />
    </div>
  );
}

export default App;
