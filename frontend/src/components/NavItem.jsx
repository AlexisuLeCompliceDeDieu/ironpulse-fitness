import { Link } from "react-router-dom";

export default function NavItem({ to, children }) {
  return (
    <Link to={to} style={linkStyle}>
      {children}
    </Link>
  );
}

const linkStyle = {
  color: "#fff",
  textDecoration: "none",
  padding: "0.4rem 0.7rem",
  borderRadius: "6px",
};
