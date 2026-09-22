import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;

/** A real servlet packaged as ROOT.war and served by Tomcat. */
public class HelloServlet extends HttpServlet {
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException {
        response.setContentType("text/plain;charset=UTF-8");
        if ("/health".equals(request.getRequestURI())) {
            response.getWriter().println("OK");
            return;
        }
        response.getWriter().println("Yubarta manual Java lab");
        response.getWriter().println("Server: " + getServletContext().getServerInfo());
        response.getWriter().println("JVM PID: " + ProcessHandle.current().pid());
    }
}
