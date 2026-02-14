export type ClothingCategory = "tops" | "bottoms" | "shoes" | "outerwear" | "accessories" | "dresses";

export interface OutfitItem {
  id: string;
  name: string;
  brand: string;
  price: number;
  image_url: string; // transparent PNG URL (bg removed)
  buy_url: string;
  category: ClothingCategory;
}

export interface OutfitRecommendation {
  recommendation_id: string;
  items: OutfitItem[];
  explanation: string;
}
