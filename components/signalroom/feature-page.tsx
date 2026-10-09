import { redirect } from 'next/navigation'

export function SignalroomFeaturePage({
  title,
  description,
  eyebrow,
}: {
  title: string
  description: string
  eyebrow: string
}): never {
  const slug = title.toLowerCase().replaceAll(' ', '-')
  redirect(`/?view=${slug}`)
}
