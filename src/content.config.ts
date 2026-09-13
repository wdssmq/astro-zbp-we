import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod'

const issues = defineCollection({
	loader: glob({ pattern: '**/*.md', base: './src/content/issues' }),
	schema: z.object({
		type: z.enum(['rss', 'app']),
		name: z.string(),
		description: z.string(),
		tags: z.array(z.string()).default([]),
		rssUrl: z.url().optional(),
		gitRepoUrl: z.url().optional(),
		canonicalUrl: z.url().optional(),
		issueNumber: z.number().int().optional(),
		issueTitle: z.string().optional(),
		issueUrl: z.url().optional(),
		updatedAt: z.string().optional(),
		collectedAt: z.string().optional(),
	}),
});

const blog = defineCollection({
	loader: glob({ pattern: '**/*.md', base: './src/content/blog' }),
	schema: z.object({
		title: z.string(),
		description: z.string().optional(),
		publishedAt: z.coerce.date().optional(),
		tags: z.array(z.string()).default([]),
	}),
});

export const collections = { issues, blog };
