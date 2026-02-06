# Document Chunking Process Visualization

## Overview

The `DocumentProcessor` class in `backend/document_processor.py` handles text chunking with sentence-aware splitting and configurable overlap.

---

## Chunking Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      RAW DOCUMENT                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Course Title: Introduction to Python                      │  │
│  │ Course Link: https://example.com                          │  │
│  │ Course Instructor: John Doe                               │  │
│  │                                                           │  │
│  │ Lesson 1: Getting Started                                 │  │
│  │ Python is a versatile language. It supports multiple...   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   STEP 1: METADATA EXTRACTION                   │
├─────────────────────────────────────────────────────────────────┤
│  • Parse Course Title (Line 1)                                  │
│  • Parse Course Link (Line 2)                                   │
│  • Parse Instructor Name (Line 3)                               │
│  • Identify Lesson Markers (Lesson X: Title)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                STEP 2: TEXT NORMALIZATION                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Input:  "Python is   a versatile\n\nlanguage.  It supports..." │
│                              │                                  │
│                              ▼                                  │
│  Output: "Python is a versatile language. It supports..."       │
│                                                                 │
│  • Collapse multiple whitespace → single space                  │
│  • Strip leading/trailing whitespace                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 3: SENTENCE SPLITTING                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Regex Pattern: (?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\!|\?)\s+   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ "Python is versatile. It supports OOP. Dr. Smith says   │    │
│  │  it's great! What do you think?"                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────┐ ┌──────────────────┐                  │
│  │ "Python is versatile"│ │ "It supports OOP"│                  │
│  └──────────────────────┘ └──────────────────┘                  │
│  ┌───────────────────────────────┐ ┌────────────────────────┐   │
│  │ "Dr. Smith says it's great!" │ │ "What do you think?"   │   │
│  └───────────────────────────────┘ └────────────────────────┘   │
│                                                                 │
│  Handles: . ! ? endings (ignores abbreviations like Dr.)        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 4: CHUNK CREATION WITH OVERLAP                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Parameters:                                                    │
│  • chunk_size: Maximum characters per chunk                     │
│  • chunk_overlap: Characters to repeat between chunks           │
│                                                                 │
│  ═══════════════════════════════════════════════════════════    │
│                                                                 │
│  Example: chunk_size=100, chunk_overlap=20                      │
│                                                                 │
│  Sentences: [S1=40chars] [S2=35chars] [S3=45chars] [S4=30chars] │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ CHUNK 1                                                 │    │
│  │ ┌────────────────┐ ┌─────────────────┐                  │    │
│  │ │      S1        │ │       S2        │  = 75 chars      │    │
│  │ └────────────────┘ └─────────────────┘                  │    │
│  │                         ▲                               │    │
│  │                    overlap zone                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ CHUNK 2                                                 │    │
│  │ ┌─────────────────┐ ┌──────────────────┐                │    │
│  │ │       S2        │ │        S3        │ = 80 chars     │    │
│  │ └─────────────────┘ └──────────────────┘                │    │
│  │  ▲                        ▲                             │    │
│  │  overlapped              overlap zone                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ CHUNK 3                                                 │    │
│  │ ┌──────────────────┐ ┌───────────────┐                  │    │
│  │ │        S3        │ │      S4       │  = 75 chars      │    │
│  │ └──────────────────┘ └───────────────┘                  │    │
│  │  ▲                                                      │    │
│  │  overlapped                                             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│             STEP 5: CONTEXT ENRICHMENT                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  First chunk of each lesson gets context prefix:                │
│                                                                 │
│  Before: "Python is a versatile language..."                    │
│                              │                                  │
│                              ▼                                  │
│  After:  "Lesson 1 content: Python is a versatile language..."  │
│                                                                 │
│  Last lesson chunks get full context:                           │
│  "Course [Title] Lesson [N] content: [chunk text]"              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FINAL OUTPUT                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CourseChunk Objects:                                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ {                                                         │  │
│  │   content: "Lesson 1 content: Python is versatile...",    │  │
│  │   course_title: "Introduction to Python",                 │  │
│  │   lesson_number: 1,                                       │  │
│  │   chunk_index: 0                                          │  │
│  │ }                                                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ {                                                         │  │
│  │   content: "It supports OOP and functional...",           │  │
│  │   course_title: "Introduction to Python",                 │  │
│  │   lesson_number: 1,                                       │  │
│  │   chunk_index: 1                                          │  │
│  │ }                                                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│                    Stored in ChromaDB                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Overlap Algorithm Detail

```
┌────────────────────────────────────────────────────────────────────┐
│                    OVERLAP CALCULATION                             │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Current chunk sentences: [S1, S2, S3, S4]                         │
│  chunk_overlap = 50 characters                                     │
│                                                                    │
│  Count backwards from end:                                         │
│                                                                    │
│    S4 (30 chars) → 30 <= 50 ✓  overlap_sentences = 1               │
│    S3 (25 chars) → 30 + 25 = 55 > 50 ✗  STOP                       │
│                                                                    │
│  Result: Next chunk starts at S4 (1 sentence overlap)              │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Chunk N:   [S1] [S2] [S3] [S4]                               │   │
│  │                          ════                                │   │
│  │                         overlap                              │   │
│  │ Chunk N+1:               [S4] [S5] [S6] [S7]                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Why Overlap Matters

```
Without Overlap:                    With Overlap:
┌──────────┐ ┌──────────┐          ┌──────────┐ ┌──────────┐
│ Chunk 1  │ │ Chunk 2  │          │ Chunk 1  │ │ Chunk 2  │
│          │ │          │          │       ═══│═│══        │
│ ...about │ │ Python   │          │ ...about │ │ about    │
│ lists.   │ │ dicts... │          │ lists.   │ │ lists.   │
└──────────┘ └──────────┘          └──────────┘ │ Python   │
                                                │ dicts... │
Query: "lists in Python"                        └──────────┘
Result: May miss context           Query: "lists in Python"
                                   Result: Full context preserved
```

---

## Configuration

| Parameter | Description | Impact |
|-----------|-------------|--------|
| `chunk_size` | Max characters per chunk | Larger = more context, slower search |
| `chunk_overlap` | Characters repeated between chunks | Higher = better continuity, more storage |
