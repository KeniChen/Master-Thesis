import { toPng } from "html-to-image";
import { jsPDF } from "jspdf";

export interface ExportOptions {
  filename?: string;
  scale?: number;
}

export async function exportToPDF(
  element: HTMLElement,
  options: ExportOptions = {}
): Promise<void> {
  const { filename = "export", scale = 5 } = options;

  const dataUrl = await toPng(element, {
    pixelRatio: scale,
    backgroundColor: "#ffffff",
    cacheBust: true,
    skipFonts: true,
  });

  // Load image to get dimensions
  const img = new Image();
  await new Promise<void>((resolve, reject) => {
    img.onload = () => resolve();
    img.onerror = reject;
    img.src = dataUrl;
  });

  const imgWidth = img.width;
  const imgHeight = img.height;

  const pdf = new jsPDF({
    orientation: imgWidth > imgHeight ? "landscape" : "portrait",
    unit: "px",
    format: [imgWidth / scale, imgHeight / scale],
  });

  pdf.addImage(dataUrl, "PNG", 0, 0, imgWidth / scale, imgHeight / scale);
  pdf.save(`${filename}.pdf`);
}
