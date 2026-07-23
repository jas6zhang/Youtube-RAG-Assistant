# Privacy Policy — YouTube RAG Helper

**Last updated: July 22, 2026**

YouTube RAG Helper ("the extension") is a Chrome extension that lets you ask
questions about the YouTube video you are currently watching and returns answers
with clickable timestamps. This policy explains what data the extension handles
and why.

## What we collect

The extension only processes the minimum needed to answer your question:

- **The current video's ID** — read from the YouTube page URL, so the extension
  knows which video you are asking about.
- **The question you type** — the text you enter in the assistant's input box.

The extension does **not** collect your name, email, address, passwords,
payment information, location, browsing history, or any personally identifiable
information. It does not create an account, and it does not track your activity
across websites.

## How we use it

When you load a video or ask a question, the video ID and your question are sent
over HTTPS to the extension's backend service. The backend:

1. Fetches the video's transcript (from YouTube captions, or by transcribing the
   audio when captions are unavailable).
2. Performs a semantic search over the transcript to find the relevant sections.
3. Uses the OpenAI API to generate an answer and identify supporting timestamps.

This is the extension's single purpose. Your data is used only to produce the
answer you requested.

## Data sharing and retention

- **Transcripts** for a video may be cached by the backend so repeated questions
  about the same video are faster and cheaper. Transcripts are derived from
  publicly available video content.
- **Your questions** are sent to the OpenAI API to generate a response. They are
  not sold, and they are not used for advertising, profiling, creditworthiness,
  or any purpose unrelated to answering your question.
- We use the following third-party service providers strictly to deliver the
  extension's functionality:
  - **OpenAI** — to generate answers and (when needed) transcribe audio.
    See the [OpenAI Privacy Policy](https://openai.com/policies/privacy-policy).
  - **The hosting provider** running the backend service.

We do **not** sell or transfer your data to third parties outside of these
service-provider use cases.

## Your choices

The extension only acts on the video you are watching and the question you type.
If you do not ask a question, no question data is sent. You can remove the
extension at any time from `chrome://extensions`.

## Changes to this policy

If this policy changes, the "Last updated" date above will be revised.

## Contact

Questions about this policy can be filed as an issue at:
https://github.com/jas6zhang/Youtube-RAG-Assistant/issues
