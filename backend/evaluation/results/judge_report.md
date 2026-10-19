# LLM-as-judge results

Generator: `openai/gpt-oss-120b`  |  Judge: `qwen/qwen3.8-27b` (different model)  |  Scale 1-5

- **Overall average: 4.06/5**  (8 of 8 cases judged)
- Criteria scored 4 or 5: **75%**
- Programmatic checks passed: **16/16**

| Output type | Cases | Avg score (1-5) |
|---|---|---|
| ppt | 1 | 4.5 |
| reading | 1 | 4.25 |
| quiz | 1 | 3.75 |
| qa | 3 | 4.0 |
| email | 2 | 4 |

## Per case

| Case | Request | Avg | Checks | Time |
|---|---|---|---|---|
| ppt-1 | Make a 6 slide ppt for eval-class on neural network bas | 4.5 | slide_count: pass, routed_to_ppt: pass | 14.7s |
| reading-1 | Make reading material for eval-class | 4.25 | routed_to_reading: pass | 10.2s |
| quiz-1 | Make a quiz of 6 questions for eval-class | 3.75 | question_count: pass, mcq_have_4_options: pass, all_have_answers: pass, routed_to_quiz: pass | 4.7s |
| qa-1 | What is a neural network? | 3.5 | routed_to_qa: pass | 15.3s |
| qa-2 | Explain the difference between supervised and unsupervi | 4.25 | routed_to_qa: pass | 12.1s |
| qa-3 | Why is ReLU preferred over the sigmoid activation funct | 4.25 | routed_to_qa: pass | 4.2s |
| email-1 | Send mail to test@example.com that tomorrow's class is  | 5 | paused_for_approval: pass, attachment_correct: pass, routed_to_email: pass | 15.6s |
| email-2 | Email the reading material of eval-class to test@exampl | 3 | paused_for_approval: pass, attachment_correct: pass, routed_to_email: pass | 4.8s |

## Judge's reasons (lowest score per case)

- **ppt-1** lowest: topic_coverage = 4: Covers neurons, activation, training, an example, and modern nets, but omits core basics like backpropagation and loss functions in detail.
- **reading-1** lowest: topic_coverage = 4: Covers neurons, layers, supervised training, gradient descent, a worked example, and the evolution to deep nets, giving a solid overview of neural network basics.
- **quiz-1** lowest: coverage_and_variety = 3: Covers activation functions, training loop, AlexNet, and depth/width trade-offs, but all 4 MCQs are single-fact recall and there is no true/false, fill-in, or diagram-based item, limiting variety.
- **qa-1** lowest: faithfulness_to_sources = 3: Most claims are grounded in the provided pages (stacked neurons, price example, BRNN properties, activation functions), but several items (loss functions, optimizers, CNNs, end-to-end learning) are not in the source material.
- **qa-2** lowest: faithfulness_to_sources = 3: Supervised claims (labeled y, real estate/price example, applications like speech recognition, machine translation, autonomous driving) are supported by the book excerpt, but the unsupervised section relies on external web citations and invented examples (clustering, anomaly detection, topic modeling) not present in the provided source material.
- **qa-3** lowest: faithfulness_to_sources = 3: Most claims are grounded in the notes (vanishing gradients, faster training, leaky ReLU), but several points (sparse activation as regularizer, computational cheapness, softmax output layer) are not in the provided source material.
- **email-1** lowest: follows_teacher_request = 5: The email correctly states that tomorrow's class is moved to 11 am and is addressed to test@example.com, matching the request.
- **email-2** lowest: no_invented_facts = 2: Invents a specific filename 'eval-class-reading-material.pdf' and claims it was 'also emailed' to the same address, which the teacher did not state.
