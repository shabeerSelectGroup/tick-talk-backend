import { resolveMediaUrl } from '@/utils/mediaUrl'

type SelfieMediaFields = {
  image_url?: string | null
  thumbnail_url?: string | null
  selfie_image_url?: string | null
  selfie_thumbnail_url?: string | null
}

/** Full-size selfie for display; thumbnails are only for tiny previews. */
export function selfieDisplayUrl(selfie: SelfieMediaFields): string {
  const url =
    selfie.selfie_image_url ||
    selfie.image_url ||
    selfie.selfie_thumbnail_url ||
    selfie.thumbnail_url
  return resolveMediaUrl(url)
}
