import { describe, expect, it } from "vitest";
import { buildReceiptUploadLinks } from "@/lib/receipt-upload-links";
import type { Receipt, ReceiptUpload } from "@/lib/types";

const receipt = (fileName: string): Receipt => ({
  file_name: fileName,
  date: null,
  seller: null,
  address: null,
  inn: null,
  amount: "100.00",
  expense_type: "такси",
  comment: null,
  route: null,
  fiscal_number: null,
  check_number: null,
  shift_number: null,
  kkt_number: null,
  fiscal_document_number: null,
  fiscal_drive_number: null,
  fiscal_sign: null,
  payment_type: null,
  qr_raw: null,
});

const upload = (id: string, fileName: string): ReceiptUpload => ({
  id,
  original_name: fileName,
  mime_type: "application/pdf",
  size: 100,
  receipt: receipt(fileName),
  created_at: "2026-08-29T10:00:00Z",
});

describe("buildReceiptUploadLinks", () => {
  it("links uploaded files to their current receipt rows", () => {
    expect(buildReceiptUploadLinks(
      [receipt("first.pdf"), receipt("manual"), receipt("second.pdf")],
      [upload("u1", "first.pdf"), upload("u2", "second.pdf")],
    )).toEqual([
      { upload_id: "u1", receipt_index: 0 },
      { upload_id: "u2", receipt_index: 2 },
    ]);
  });

  it("matches duplicate file names to different rows", () => {
    expect(buildReceiptUploadLinks(
      [receipt("same.pdf"), receipt("same.pdf")],
      [upload("u1", "same.pdf"), upload("u2", "same.pdf")],
    )).toEqual([
      { upload_id: "u1", receipt_index: 0 },
      { upload_id: "u2", receipt_index: 1 },
    ]);
  });
});
