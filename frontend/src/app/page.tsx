import { redirect } from "next/navigation";

export default function RootIndex() {
  // The (app) route group owns `/`; this file exists only because route groups
  // don't carve a page on their own. Redirect to the dashboard explicitly.
  redirect("/dashboard");
}
