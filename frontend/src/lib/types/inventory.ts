export interface InventoryItem {
  id: number;
  centre_id: number;
  item_name: string;
  category?: string | null;
  expected_quantity: number;
  created_at: string;
  updated_at: string;
}

export interface InventoryItemCreateInput {
  item_name: string;
  category?: string | null;
  expected_quantity: number;
}

export interface InventoryItemUpdateInput {
  item_name?: string;
  category?: string | null;
  expected_quantity?: number;
}

export interface InventoryRowError {
  row: number;
  field?: string | null;
  message: string;
}

export interface InventoryParsedItem {
  row: number;
  item_name: string;
  category?: string | null;
  expected_quantity: number;
}

export interface InventoryUploadPreviewResponse {
  is_valid: boolean;
  filename: string;
  total_rows: number;
  valid_rows_count: number;
  error_count: number;
  items: InventoryParsedItem[];
  errors: InventoryRowError[];
}

export interface InventoryConfirmRequest {
  items: Array<{
    item_name: string;
    category?: string | null;
    expected_quantity: number;
  }>;
  replace_existing: boolean;
}

export interface InventoryConfirmResponse {
  message: string;
  imported_count: number;
  replaced_count: number;
  centre_id: number;
}
