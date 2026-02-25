public void testCpioUnarchiveCreatedByRedlineRpm() throws Exception {
        CpioArchiveInputStream in =
            new CpioArchiveInputStream(new FileInputStream(getFile("redline.cpio")));
        CpioArchiveEntry entry= null;

        int count = 0;
        while ((entry = (CpioArchiveEntry) in.getNextEntry()) != null) {
            count++;
        }
        in.close();

        assertEquals(count, 1);
    }