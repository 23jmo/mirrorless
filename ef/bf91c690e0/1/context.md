# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Simplify Extraction to LLM-Only + Fix HTML Bodies

## Context

The regex extraction pipeline has compounding edge cases: summary lines captured as items ("Subtotal:", "Tax:"), SKUs as item names ("140953SCHV1"), raw HTML bodies fed to regex producing garbage, and non-fashion emails (Robinhood, Starbucks) slipping through. Haiku is essentially free via the OAuth token method, so we optimize purely for accuracy: replace the regex+subject-fallback+LLM-fallback chain...

### Prompt 2

always exracting nothing: --- Email 78/79 ---

  Subject: Your subscription confirmation
  Sender:  Epidemic Sound <noreply@accounts.epidemicsound.com>
 Subscription: Perso..."cription:firmation

  Brand: Accounts  |  Merchant: Accounts
  Method: LLM (sending to Claude Haiku)
  LLM input:
    Subject: Your subscription confirmation
    Body: Your subscription confirmation

Your free trial is now active
 for the following subscription:

Subscription: Personal
Date of purchase: Feb 22, 2024
Price:...

### Prompt 3

wait honestly the more purchase data the more potential context - let's scrape all purchase data but just make sure we categorize it in the purchases database so we can easily flag by fashion-related or not. Thoughts?

