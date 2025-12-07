import React, { useState, useEffect } from "react";
import apiClient from "../../lib/api-client";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";

export default function ModifyDish() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { dishId } = useParams<{ dishId: string }>();

  const [name, setName] = useState<string | undefined>();
  const [description, setDescription] = useState<string | undefined>();
  const [cost, setCost] = useState<string | undefined>(); // dollars
  const [image, setImage] = useState<File | null>(null);
  const [existingImage, setExistingImage] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // 1️⃣ Fetch existing dish
  useEffect(() => {
    if (!dishId) return;

    apiClient
      .get(`/dishes/${dishId}`)
      .then((res) => {
        const dish = res.data;
        setName(dish.name);
        setDescription(dish.description);
        setCost((dish.cost / 100).toFixed(2)); // cents → dollars
        setExistingImage(dish.picture || null);
      })
      .catch((err) => console.error("Failed to fetch dish:", err))
      .finally(() => setLoading(false));
  }, [dishId]);

  // 2️⃣ Handle submit (partial updates)
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !dishId) return;

    setSubmitting(true);

    const formData = new FormData();
    const updateData: any = {};

    if (name !== undefined) updateData.name = name;
    if (description !== undefined) updateData.description = description;
    if (cost !== undefined && cost !== "") updateData.cost = Math.round(parseFloat(cost) * 100);

    formData.append("dish_data", JSON.stringify(updateData));

    if (image) formData.append("image", image); // optional new image

    try {
      await apiClient.put(`/dishes/${dishId}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      navigate("/chef/dashboard");
    } catch (err) {
      console.error("Failed to update dish:", err);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <p>Loading dish data...</p>;

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Modify Dish</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Dish Name */}
        <div>
          <label className="block font-medium mb-1">Dish Name</label>
          <input
            type="text"
            className="input w-full"
            value={name || ""}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        {/* Description */}
        <div>
          <label className="block font-medium mb-1">Description</label>
          <textarea
            className="input w-full h-28"
            value={description || ""}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        {/* Cost */}
        <div>
          <label className="block font-medium mb-1">Price (USD)</label>
          <input
            type="number"
            className="input w-full"
            value={cost || ""}
            onChange={(e) => setCost(e.target.value)}
            min="0"
            step="0.01"
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

        {/* Preview: new or existing */}
        {(image || existingImage) && (
          <div className="mt-4">
            <p className="text-sm text-gray-600 mb-1">Preview:</p>
            <img
              src={image ? URL.createObjectURL(image) : existingImage!}
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
          {submitting ? "Updating..." : "Update Dish"}
        </button>
      </form>
    </div>
  );
}
