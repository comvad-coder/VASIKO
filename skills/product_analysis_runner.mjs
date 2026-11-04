import { readFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'

const input = JSON.parse(readFileSync(0, 'utf8'))
const library = process.env.VASIKO_LLM_LIB || '/home/ubuntu/skills/builtin-llm-models/lib/llm.mjs'
const { LlmClient, messageText } = await import(pathToFileURL(library).href)

const schema = {
  type: 'object',
  properties: {
    executive_summary: { type: 'string' },
    product_positioning: { type: 'string' },
    target_audience: { type: 'array', items: { type: 'string' } },
    value_propositions: { type: 'array', items: { type: 'string' } },
    strengths: { type: 'array', items: { type: 'string' } },
    risks_and_gaps: { type: 'array', items: { type: 'string' } },
    recommended_channels: { type: 'array', items: { type: 'string' } },
    next_internal_actions: { type: 'array', items: { type: 'string' } },
    confidence: { type: 'string', enum: ['low', 'medium', 'high'] },
  },
  required: [
    'executive_summary', 'product_positioning', 'target_audience',
    'value_propositions', 'strengths', 'risks_and_gaps',
    'recommended_channels', 'next_internal_actions', 'confidence',
  ],
  additionalProperties: false,
}

const llm = new LlmClient({ timeoutMs: 120000, maxRetries: 2 })
const response = await llm.chat({
  model: 'gpt-6-luna',
  messages: [
    {
      role: 'system',
      content: 'Ты product analyst ВАСИКО. Анализируй только переданные данные URL-check. Не выдумывай факты, явно отмечай пробелы. Не выполняй внешние действия. Верни только JSON по схеме.',
    },
    {
      role: 'user',
      content: JSON.stringify({
        objective: input.objective,
        product_url: input.product_url,
        url_check_report: input.url_check_report,
      }),
    },
  ],
  max_completion_tokens: 5000,
  reasoning: { effort: 'low' },
  response_format: {
    type: 'json_schema',
    json_schema: { name: 'product_analysis', strict: true, schema },
  },
})

const text = messageText(response)
process.stdout.write(JSON.stringify({
  provider: 'manus-builtin',
  model: 'gpt-6-luna',
  analysis: JSON.parse(text),
  usage: response.usage || null,
}))
