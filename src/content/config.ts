import { defineCollection, z } from 'astro:content';

const billsCollection = defineCollection({
  type: 'content',
  schema: z.object({
    // Core Metadata
    id: z.string(),
    title: z.string(),
    shortTitle: z.string(),
    billNumber: z.string(),
    status: z.enum(['draft', 'committee', 'debate', 'vote', 'passed', 'enacted']),
    priority: z.enum(['urgent', 'important', 'normal']),
    dateIntroduced: z.string(),
    dateUpdated: z.string(),
    sectionsCount: z.number(),
    pdfUrl: z.string(),

    // Categorization
    categories: z.array(z.string()),
    affects: z.array(z.string()),

    // Video
    notebookLMVideo: z.object({
      url: z.string(),
      duration: z.string().optional(),
      transcript: z.string().optional(),
    }).optional(),

    // Impact Ratings
    impacts: z.object({
      innovation: z.object({
        level: z.enum(['positive', 'mixed', 'negative']),
        severity: z.enum(['low', 'moderate', 'high']),
      }).optional(),
      freeSpeech: z.object({
        level: z.enum(['positive', 'mixed', 'negative']),
        severity: z.enum(['low', 'moderate', 'high']),
      }).optional(),
      privacy: z.object({
        level: z.enum(['positive', 'mixed', 'negative']),
        severity: z.enum(['low', 'moderate', 'high']),
      }).optional(),
      business: z.object({
        level: z.enum(['positive', 'mixed', 'negative']),
        severity: z.enum(['low', 'moderate', 'high']),
      }).optional(),
      legalProcess: z.object({
        level: z.enum(['positive', 'mixed', 'negative']),
        severity: z.enum(['low', 'moderate', 'high']),
      }).optional(),
      civilSociety: z.object({
        level: z.enum(['positive', 'mixed', 'negative']),
        severity: z.enum(['low', 'moderate', 'high']),
      }).optional(),
    }),

    // Related Bills
    relatedBills: z.array(z.object({
      id: z.string(),
      relationship: z.enum(['overlap', 'conflict', 'complement', 'amends']),
      description: z.string(),
    })).optional(),

    // Key Concerns
    topConcerns: z.array(z.string()),

    // Action Items
    actionItems: z.object({
      publicComment: z.object({
        enabled: z.boolean(),
        deadline: z.string().optional(),
        submissionEmail: z.string().optional(),
        guideUrl: z.string().optional(),
      }).optional(),
      nextHearing: z.object({
        date: z.string(),
        time: z.string(),
        location: z.string(),
      }).optional(),
      mpContact: z.object({
        enabled: z.boolean(),
        findRepUrl: z.string().optional(),
      }).optional(),
      petitionLink: z.string().optional(),
    }).optional(),

    // Status Timeline
    timeline: z.array(z.object({
      stage: z.string(),
      date: z.string().nullable(),
      completed: z.boolean(),
      current: z.boolean().optional(),
    })).optional(),
  }),
});

export const collections = {
  bills: billsCollection,
};
