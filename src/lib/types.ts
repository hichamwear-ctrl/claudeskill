export type CategoryType = "SUBTRACTION" | "ADDITION";

export interface CategoryDTO {
  id: string;
  name: string;
  icon: string;
  type: CategoryType;
  isCustom: boolean;
  isSystem: boolean;
}

export interface ExpenseLineDTO {
  id: string;
  monthId: string;
  categoryId: string;
  amount: number;
  createdAt: string;
  category: CategoryDTO;
}

export interface MonthListItem {
  id: string;
  label: string;
  clientPayment: number;
  remainder: number;
  kharja: { id: string; net: number } | null;
}

export interface MonthDetail {
  id: string;
  label: string;
  clientPayment: number;
  remainder: number;
  expenses: ExpenseLineDTO[];
  kharja: KharjaDTO | null;
}

export interface KharjaLineDTO {
  id: string;
  kharjaId: string;
  type: "IN" | "OUT";
  amount: number;
  note: string;
  createdAt: string;
}

export interface KharjaDTO {
  id: string;
  monthId: string;
  net?: number;
  lines: KharjaLineDTO[];
}

export interface CapitalDTO {
  total: number;
  breakdown: { id: string; label: string; remainder: number; kharjaNet: number }[];
}

export interface RDebtLineDTO {
  id: string;
  type: "INCREASE" | "REPAYMENT";
  paymentMethod: "CASH" | "TRANSFER" | null;
  amountGross: number;
  amountNet: number;
  createdAt: string;
}

export interface RDebtDTO {
  id: string;
  baseAmount: number;
  balance: number;
  lines: RDebtLineDTO[];
}
