import React, { useState } from "react";
import apiClient from "../../lib/api-client";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";

export default function CreateDish() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [cost, setCost] = useState(""); // user enters dollars, not cents
  const [image, setImage] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;

    setSubmitting(true);

    const formData = new FormData();
    formData.append(
      "dish_data",
      JSON.stringify({
        name,
        description,
        cost: Math.round(parseFloat(cost) * 100), // convert to cents
      })
    );

    if (image) {
      formData.append("image", image);
    }

    try {
      await apiClient.post("/dishes", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      navigate("/chef/dashboard");
    } catch (err) {
      console.error("Failed to create dish:", err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Create New Dish</h1>

      <form onSubmit={handleSubmit} className="space-y-6">

        {/* Dish Name */}
        <div>
          <label className="block font-medium mb-1">Dish Name</label>
          <input
            type="text"
            className="input w-full"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>

        {/* Description */}
        <div>
          <label className="block font-medium mb-1">Description</label>
          <textarea
            className="input w-full h-28"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
          />
        </div>

        {/* Cost */}
        <div>
          <label className="block font-medium mb-1">Price (USD)</label>
          <input
            type="number"
            className="input w-full"
            value={cost}
            onChange={(e) => setCost(e.target.value)}
            min="0"
            step="0.01"
            required
          />
        </div>

        {/* Image Upload */}
        <div>
          <label className="block font-medium mb-1">Image</label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) =>
              e.target.files?.[0] ? setImage(e.target.files[0]) : null
            }
          />
        </div>

        {/* Preview image */}
        {image && (
          <div className="mt-4">
            <p className="text-sm text-gray-600 mb-1">Preview:</p>
            <img
              src={URL.createObjectURL(image)}
              alt="Preview"
              className="w-48 rounded shadow"
            />
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={submitting}
          className={`btn-primary ${submitting ? "opacity-70" : ""}`}
        >
          {submitting ? "Creating..." : "Create Dish"}
        </button>
      </form>
    </div>
  );
}
