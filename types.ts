/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/

export interface Product {
  SKU: string;
  Code: string;
  Category: string;
  Number: string;
  Name: string;
  ImageFile: string;
  Stock: number;
  Location: string;
  SN: string;
  WarrantyStart: string | null;
  WarrantyEnd: string | null;
  Accessories: string;
}

export type LogType = '入庫' | '出庫' | '新增' | '修改' | '刪除';

export interface LogEntry {
  Time: string;
  User: string;
  Type: LogType;
  SKU: string;
  Name: string;
  Quantity: number;
  Note: string;
}

export type Page = 'overview' | 'inbound' | 'outbound' | 'maintenance' | 'logs' | 'warranty';
