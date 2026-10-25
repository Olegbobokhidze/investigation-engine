import { fileTypeLabels, type FileType } from "@/shared/fileTypes";

interface FileTypeTagProps {
  fileType: FileType;
}

export function FileTypeTag({ fileType }: FileTypeTagProps) {
  return (
    <span className="inline-block shrink-0 rounded-[5px] border border-border bg-surface px-1.5 py-0.75 font-mono text-2xs font-medium tracking-wide text-ink-secondary">
      {fileTypeLabels[fileType]}
    </span>
  );
}
