import type { CorpusDocument } from "@/features/documents/types";
import type { Investigation } from "@/features/investigations/types";

const datasetCreatedAt = "2026-10-25T12:00:00Z";

const incidentFiles: Pick<CorpusDocument, "id" | "title" | "fileType" | "chunkCount">[] = [
  {
    id: "doc_8f2c41",
    title: "INC-0412 Payment latency, 14 March.pdf",
    fileType: "pdf",
    chunkCount: 18,
  },
  { id: "doc_31aa07", title: "changelog-2024-03.md", fileType: "md", chunkCount: 42 },
  { id: "doc_c90b12", title: "checkout-api runbook.docx", fileType: "docx", chunkCount: 27 },
  { id: "doc_5d7e93", title: "ledger-worker postmortem.md", fileType: "md", chunkCount: 31 },
];

const incidentDocuments: CorpusDocument[] = incidentFiles.map((file) => ({
  ...file,
  origin: "dataset",
  createdAt: datasetCreatedAt,
}));

const hotpotTitles = [
  "Scott Derrickson",
  "Ed Wood",
  "Ed Wood (film)",
  "Doctor Strange (2016 film)",
  "Kiss and Tell (1945 film)",
  "Shirley Temple",
  "Corliss Archer",
  "Adriana Trigiani",
  "Big Stone Gap (film)",
  "Greenwich Village",
  "The Saimaa Gesture",
  "Finnish rock",
  "Laleli Mosque",
  "Esma Sultan Mansion",
  "Allie Goertz",
  "Milhouse Van Houten",
  "Matt Groening",
  "Arthur's Magazine",
  "First for Women",
  "The Oberoi Group",
  "Jonny Craig",
  "Pete Doherty",
  "Eenasul Fateh",
  "Mick Jagger",
];

const hotpotDocuments: CorpusDocument[] = hotpotTitles.map((title, index) => ({
  id: `hotpot_${String(index + 1).padStart(6, "0")}`,
  title,
  fileType: "txt",
  chunkCount: 1,
  origin: "dataset",
  createdAt: datasetCreatedAt,
}));

export const initialDocuments: CorpusDocument[] = [...incidentDocuments, ...hotpotDocuments];

export const answeredInvestigation: Omit<Investigation, "id" | "question"> = {
  status: "answered",
  answer: [
    "Payment processing slowed on 14 March after two changes shipped the same morning. The connection pool for payments-db was reduced from 50 to 20 connections in CHG-2291 [1][2], and a new 3-second fraud-scoring timeout was added to checkout-api in CHG-2294 [3].",
    "Requests that timed out were retried and queued, so ledger-worker fell behind, with consumer lag peaking at 41 minutes [1][4].",
  ].join("\n\n"),
  sources: [
    {
      number: 1,
      documentId: "doc_8f2c41",
      documentTitle: "INC-0412 Payment latency, 14 March.pdf",
      fileType: "pdf",
      excerpt:
        "…the first alerts fired at 09:12, when checkout-api p95 latency passed 4 s and ledger-worker lag began to climb…",
    },
    {
      number: 2,
      documentId: "doc_31aa07",
      documentTitle: "changelog-2024-03.md",
      fileType: "md",
      excerpt:
        "…14 Mar · CHG-2291 deployed 09:40 — payments-db pool size 50 → 20 (owner: platform-data)…",
    },
    {
      number: 3,
      documentId: "doc_c90b12",
      documentTitle: "checkout-api runbook.docx",
      fileType: "docx",
      excerpt:
        "…since CHG-2294, fraud scoring times out after 3 s and the request is retried once…",
    },
    {
      number: 4,
      documentId: "doc_5d7e93",
      documentTitle: "ledger-worker postmortem.md",
      fileType: "md",
      excerpt:
        "…retries amplified load; consumer lag peaked at 41 minutes before the pool change was reverted…",
    },
  ],
  conflicts: [
    {
      summary:
        "The incident report says the delays started at 09:12 [1], but the change log records CHG-2291 as deployed at 09:40 [2]. These documents can’t confirm which came first.",
    },
  ],
  steps: [
    {
      title: "Planned the investigation",
      detail: "3 sub-questions: changes in March · affected services · confirming documents",
      result: null,
    },
    {
      title: "Searched documents",
      detail: 'search_documents(query="payment delays March", k=8)',
      result: "8 results",
    },
    {
      title: "Searched documents",
      detail: 'search_documents(query="change log payments-db March", k=8)',
      result: "6 results",
    },
    { title: "Opened a document", detail: 'get_document(id="doc_8f2c41")', result: "1 document" },
    {
      title: "Verified claims against sources",
      detail: "6 claims checked · 1 conflict found",
      result: null,
    },
  ],
};

export const insufficientEvidenceInvestigation: Omit<Investigation, "id" | "question"> = {
  status: "insufficient_evidence",
  answer:
    "None of the indexed documents describe a refund policy for EU customers, so the engine won’t guess.",
  sources: [],
  conflicts: [],
  steps: [
    {
      title: "Searched documents",
      detail: 'search_documents(query="refund policy EU customers", k=8)',
      result: "0 relevant",
    },
    {
      title: "Searched documents",
      detail: 'search_documents(query="EU refunds", k=8)',
      result: "0 relevant",
    },
  ],
};
