export default function Tag({ tom = "neutro", children }) {
  return <span className={`tag tag-${tom}`}>{children}</span>;
}