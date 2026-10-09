export const motionEase = [0.22, 1, 0.36, 1] as const

export const layoutTransition = {
  duration: 0.28,
  ease: motionEase,
}

export const fadeInUp = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: layoutTransition,
}

export const stagger = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.04,
    },
  },
}

export const springTransition = {
  type: 'spring',
  stiffness: 260,
  damping: 22,
}
