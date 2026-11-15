// only same-site paths as a post-login destination ("/x", never "//evil" or "https://...")
export const safeNext = (n, dflt = '/') => (n && n.startsWith('/') && !n.startsWith('//') && !n.startsWith('/\\') ? n : dflt);
