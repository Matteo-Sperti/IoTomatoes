class IDs:
    def __init__(self, minID : int, maxID : int = -1, step = 1):
        """IDs class. Generate and manage IDs.
        
        - `minID (int)`: minimum ID,
        - `maxID (int)`: maximum ID, -1 (default) means no upper limit,
        - `step (int)`: step between consecutive IDs (default = 1)
        """
        self.minID = minID
        self.maxID = maxID
        self.step = step
        self.ID_free_list = []

    def get_ID(self):
        """Get an ID."""

        if len(self.ID_free_list) > 0:
            return self.ID_free_list.pop()
        else:
            if self.maxID != -1 and self.minID > self.maxID:
                return -1
            else:
                ID = self.minID
                self.minID += self.step
                return int(ID)

    def free_ID(self, ID : int):
        """Free an `ID`."""
        
        self.ID_free_list.append(ID)