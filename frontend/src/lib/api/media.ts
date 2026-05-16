import { apiUploadFile } from "./client";

export async function sendMedia(
  numberId: string,
  to: string,
  file: File,
  caption?: string
) {
  const form = new FormData();
  form.append("to", to);
  form.append("file", file);
  if (caption) form.append("caption", caption);
  return apiUploadFile<{ success: boolean }>(
    `/numbers/${numberId}/messages/media`,
    form
  );
}
