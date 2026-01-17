"use client";

import { useState } from "react";
import { FileDown, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { exportToPDF } from "@/lib/pdf-export";

export function ExportPDFButton() {
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    const appContainer = document.getElementById("app-container");
    if (!appContainer) {
      console.error("App container not found");
      return;
    }

    setIsExporting(true);
    try {
      // Hide elements that shouldn't be exported
      const controls = document.querySelectorAll(
        ".react-flow__controls, .react-flow__minimap"
      );
      controls.forEach((el) => ((el as HTMLElement).style.display = "none"));

      // Temporarily remove height constraint for full capture
      const originalHeight = appContainer.style.height;
      const originalOverflow = appContainer.style.overflow;
      appContainer.style.height = "auto";
      appContainer.style.overflow = "visible";

      // Also fix the content area
      const contentArea = appContainer.querySelector(
        ".flex.flex-1.overflow-hidden"
      ) as HTMLElement;
      let originalContentHeight = "";
      let originalContentOverflow = "";
      if (contentArea) {
        originalContentHeight = contentArea.style.height;
        originalContentOverflow = contentArea.style.overflow;
        contentArea.style.height = "auto";
        contentArea.style.overflow = "visible";
      }

      await exportToPDF(appContainer, {
        filename: document.title || "SAED-LLM",
        scale: 3,
      });

      // Restore original styles
      appContainer.style.height = originalHeight;
      appContainer.style.overflow = originalOverflow;
      if (contentArea) {
        contentArea.style.height = originalContentHeight;
        contentArea.style.overflow = originalContentOverflow;
      }

      // Restore hidden elements
      controls.forEach((el) => ((el as HTMLElement).style.display = ""));
    } catch (error) {
      console.error("Export failed:", error);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-9 w-9"
      onClick={handleExport}
      disabled={isExporting}
    >
      {isExporting ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <FileDown className="h-4 w-4" />
      )}
      <span className="sr-only">Export to PDF</span>
    </Button>
  );
}
