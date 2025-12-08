/**
 * Image Search Page
 * 
 * Upload a food photo and get similar dishes from the menu
 */

import React, { useState, useRef } from 'react';
import apiClient from '../lib/api-client';
import DishCard from '../components/DishCard';
import LoadingSkeleton from '../components/LoadingSkeleton';

interface DishResult {
  id: number;
  name: string;
  description: string | null;
  cost: number;
  cost_formatted: string;
  picture: string | null;
  average_rating: number;
  reviews: number;
  chefID: number | null;
  restaurantID: number;
  similarity_score?: number;
}

const ImageSearchPage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [results, setResults] = useState<DishResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchComplete, setSearchComplete] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select an image file');
      return;
    }

    // Validate file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      setError('Image is too large. Maximum size is 10MB');
      return;
    }

    setError(null);
    setSelectedFile(file);
    setSearchComplete(false);

    // Create preview URL
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
  };

  const handleSearch = async () => {
    if (!selectedFile) return;

    setIsSearching(true);
    setError(null);
    setResults([]);

    try {
      // Create form data
      const formData = new FormData();
      formData.append('file', selectedFile);

      // Send to backend
      const response = await apiClient.post<DishResult[]>(
        '/image-search',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          params: {
            top_k: 5,
          },
        }
      );

      setResults(response.data);
      setSearchComplete(true);
    } catch (err: any) {
      console.error('Image search failed:', err);
      setError(
        err.response?.data?.detail || 
        'Failed to search. Please try again.'
      );
    } finally {
      setIsSearching(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResults([]);
    setError(null);
    setSearchComplete(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith('image/')) {
      const event = {
        target: {
          files: [file],
        },
      } as any;
      handleFileSelect(event);
    } else {
      setError('Please drop an image file');
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          🔍 Search by Image
        </h1>
        <p className="text-gray-600">
          Upload a photo of food and we'll find similar dishes on our menu
        </p>
      </div>

      {/* Upload Section */}
      <div className="max-w-2xl mx-auto mb-8">
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center ${
            previewUrl ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
          }`}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          {previewUrl ? (
            <div className="space-y-4">
              <img
                src={previewUrl}
                alt="Preview"
                className="max-h-64 mx-auto rounded-lg shadow-md"
              />
              <p className="text-sm text-gray-600">
                {selectedFile?.name}
              </p>
              <div className="flex gap-3 justify-center">
                <button
                  onClick={handleSearch}
                  disabled={isSearching}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition"
                >
                  {isSearching ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                          fill="none"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        />
                      </svg>
                      Searching...
                    </span>
                  ) : (
                    'Search for Similar Dishes'
                  )}
                </button>
                <button
                  onClick={handleReset}
                  className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
                >
                  Reset
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                stroke="currentColor"
                fill="none"
                viewBox="0 0 48 48"
              >
                <path
                  d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <div>
                <label
                  htmlFor="file-upload"
                  className="cursor-pointer text-blue-600 hover:text-blue-700 font-medium"
                >
                  Click to upload
                </label>
                <span className="text-gray-600"> or drag and drop</span>
              </div>
              <p className="text-xs text-gray-500">
                PNG, JPG, GIF up to 10MB
              </p>
              <input
                ref={fileInputRef}
                id="file-upload"
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}
      </div>

      {/* Results Section */}
      {isSearching && (
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl font-bold mb-6">Finding similar dishes...</h2>
          <LoadingSkeleton count={5} />
        </div>
      )}

      {searchComplete && results.length > 0 && (
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl font-bold mb-6">
            Similar Dishes ({results.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {results.map((dish, index) => (
              <div key={dish.id} className="relative">
                {/* Similarity badge */}
                {dish.similarity_score !== undefined && (
                  <div className="absolute top-2 left-2 z-10 bg-blue-600 text-white px-3 py-1 rounded-full text-sm font-semibold shadow-lg">
                    #{index + 1} Match
                    {dish.similarity_score > 0 && (
                      <span className="ml-1 text-xs opacity-90">
                        ({Math.round(dish.similarity_score * 100)}%)
                      </span>
                    )}
                  </div>
                )}
                <DishCard
                  dish={{
                    id: dish.id,
                    name: dish.name,
                    description: dish.description,
                    cost: dish.cost,
                    cost_formatted: dish.cost_formatted,
                    average_rating: dish.average_rating,
                    reviews: dish.reviews,
                    picture: dish.picture,
                    chefID: dish.chefID,
                    restaurantID: dish.restaurantID || 1,
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {searchComplete && results.length === 0 && !error && (
        <div className="max-w-2xl mx-auto text-center py-12">
          <p className="text-gray-600 text-lg mb-4">
            No matching dishes found. Try a different image!
          </p>
          <button
            onClick={handleReset}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Try Another Image
          </button>
        </div>
      )}

      {/* Info Section */}
      <div className="max-w-4xl mx-auto mt-12 p-6 bg-gray-50 rounded-lg">
        <h3 className="text-lg font-semibold mb-3">How it works</h3>
        <ul className="space-y-2 text-gray-700">
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">1.</span>
            <span>Upload a photo of any food dish</span>
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">2.</span>
            <span>Our AI analyzes the visual features (colors, textures, composition)</span>
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">3.</span>
            <span>We match it against our menu to find similar dishes</span>
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">4.</span>
            <span>Get recommendations you can order right away!</span>
          </li>
        </ul>
      </div>
    </div>
  );
};

export default ImageSearchPage;
