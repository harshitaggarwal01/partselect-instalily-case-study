export interface Product {
  part_number: string;
  name: string;
  price: number | null;
  image_url: string | null;
  url: string | null;
  description: string | null;
}

export interface InstallStep {
  step_number: number;
  instruction: string;
  caution: string | null;
}

export interface TroubleshootStep {
  step_number: number;
  title: string;
  description: string;
}

interface BaseResponse {
  type: string;
  text: string;
}

export interface ProductInfoResponse extends BaseResponse {
  type: "product_info";
  products: Product[];
}

export interface InstallResponse extends BaseResponse {
  type: "install";
  part: Product | null;
  steps: InstallStep[];
  sources: string[];
  part_image_url: string | null;
}

export interface CompatibilityResponse extends BaseResponse {
  type: "compatibility";
  part: Product | null;
  model_number: string | null;
  status: "compatible" | "not_compatible" | "unknown";
  details: string | null;
}

export interface TroubleshootingResponse extends BaseResponse {
  type: "troubleshooting";
  appliance_type: "refrigerator" | "dishwasher" | null;
  issue: string | null;
  steps: TroubleshootStep[];
  sources: string[];
  part_suggestions: Product[];
}

export type ChatResponse =
  | InstallResponse
  | CompatibilityResponse
  | ProductInfoResponse
  | TroubleshootingResponse;

export interface FrontendMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
}
