// frontend/src/utils/cropImage.ts
// Center-crop an image File to a square and downscale to 512x512 JPEG.
// Returns a Blob ready for multipart upload. Throws on a non-image file.
const TARGET = 512;

export async function cropImageToSquareJpeg(file: File): Promise<Blob> {
  if (!file.type.startsWith("image/")) {
    throw new Error("Please choose an image file.");
  }
  const bitmap = await createImageBitmap(file);
  const side = Math.min(bitmap.width, bitmap.height);
  const sx = (bitmap.width - side) / 2;
  const sy = (bitmap.height - side) / 2;

  const canvas = document.createElement("canvas");
  canvas.width = TARGET;
  canvas.height = TARGET;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Could not process image.");
  ctx.drawImage(bitmap, sx, sy, side, side, 0, 0, TARGET, TARGET);
  bitmap.close(); // free GPU-backed memory (matters if called repeatedly)

  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Could not process image."))),
      "image/jpeg",
      0.85
    );
  });
}
