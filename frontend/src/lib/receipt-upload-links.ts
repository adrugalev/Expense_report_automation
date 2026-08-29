import type { Receipt, ReceiptUpload } from "@/lib/types";

export function buildReceiptUploadLinks(receipts: Receipt[], uploads: ReceiptUpload[]) {
  const usedReceiptIndexes = new Set<number>();
  return uploads.flatMap((upload) => {
    const receiptIndex = receipts.findIndex(
      (receipt, index) => !usedReceiptIndexes.has(index) && receipt.file_name === upload.receipt.file_name,
    );
    if (receiptIndex < 0) return [];
    usedReceiptIndexes.add(receiptIndex);
    return [{ upload_id: upload.id, receipt_index: receiptIndex }];
  });
}
